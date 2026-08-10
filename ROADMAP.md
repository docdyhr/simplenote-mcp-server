# Simplenote MCP — Roadmap

> Make Simplenote the best note-taking companion for Claude Desktop: achieve full Bear parity, then surpass it with Simplenote-native capabilities no other note MCP can offer — and become a first-class layer of Claude's working memory, hardened for private data.

**Current version**: v1.17.1 released; Phases 8-10 below (correctness fixes, Vault, companion architecture) merged to `main` and awaiting the next version cut — 30 tools
**Working checklist**: see [TODO.md](TODO.md)
**Supersedes**: `docs/ROADMAP.md` (deprecated)

---

## Current State — v1.17.1 + Vault

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
| `encrypt_note` | Vault-encrypt an existing note's body (AES-256-GCM); idempotent |
| `decrypt_note` | Reverse `encrypt_note`; idempotent |
| `vault_status` | Check Vault key availability, provider, and encrypted-note count |

9 read tools are always listed; the 21 write tools above are only exposed when `SIMPLENOTE_WRITE_MODE=true` (and gated per-call by a rolling write budget) — see [SECURITY.md](SECURITY.md). `create_note`/`update_note` also accept an `encrypt=true` flag (not a separate tool).

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

## Companion Hardening (v1.18+)

The Bear-parity and Simplenote-differentiator phases above are complete. These phases were prompted by a review benchmarking this project against Bear MCP and against the goal of being a genuine **Claude Desktop working-memory companion** (not just a note CRUD server).

### Phase 8 — Correctness Fixes ✅ (v1.18, unreleased)

Three concrete gaps surfaced by a full research pass (three independent codebase audits) that undercut the companion trust model — Claude and the user both read/write the same notes, so silent inconsistencies are worse here than in a single-user CRUD tool:

| # | Problem | Fix |
|---|---|---|
| 1 | `add_tags`/`remove_tags`/`update_note` don't hyphenate spaces in tags (dead code discards the correct `_parse_tags()` call) | Route all tag-accepting handlers through `ToolHandlerBase._parse_tags()`; extend `SecurityValidator` tag normalization to all 8 tag-accepting tools; unify `tags` schema to `array<string>` |
| 2 | `search_notes` has no enforced default `limit` — returns unbounded results despite documenting "default: 20" | Enforce `min(limit or 20, 100)`, matching `list_notes` |
| 3 | Notes edited outside Claude (via background sync) never get re-indexed for tags/words/titles — invisible to `list_tags`/tag-filtered search despite being fully retrievable by `get_note` | Make `_process_sync_notes()` call the same index maintenance as the create/update path; fix the `_initialized=True`-before-loaded race that silently no-ops the real cache initializer |

### Phase 9 — Vault: Opt-In Client-Side Encryption ✅ (v1.19, unreleased)

Simplenote has **no encryption at rest** — Automattic's own docs confirm staff can technically read note content and explicitly recommend against storing sensitive data there. As Simplenote MCP becomes a working-memory layer, Claude will write increasingly operational detail into it. Vault closes that gap:

- Per-note opt-in encryption (`encrypt=true` on `create_note`/`update_note`, plus `encrypt_note`/`decrypt_note` for existing notes) — most notes stay plaintext and fully searchable; only explicitly marked notes are protected.
- AEAD encryption (`cryptography` library, AES-256-GCM) with a versioned envelope format (`%%SNVAULT:v1%%` + base64 nonce/ciphertext+tag) and a `vault-encrypted` tag marker. Title (first line) always stays plaintext.
- Master key via the `keyring` library (OS keychain — macOS/Linux/Windows), fetched once per process lifetime and cached in memory only, avoiding the repeated-approval-dialog problem that made this project previously abandon Keychain storage for the Simperium token. Container/headless deployments use a `SIMPLENOTE_VAULT_KEY_FILE` escape hatch.
- `vault_status()` tool; transparent decrypt-on-read for `get_note`/`search_notes`/`list_notes` when the key is available — `{"encrypted": true, "decryptable": false}` when it isn't, never raw ciphertext.
- Vault-note bodies are excluded from the word/title index and from the search engine's candidate set — no decrypted shadow search index in v1; this is a documented tradeoff, not a gap.
- Safety guards: `add_text`/`replace_section`/`update_note` (without `encrypt=true`) refuse on Vault-encrypted notes rather than corrupt the envelope; `find_and_merge_duplicates` excludes them from comparison.
- No multi-device key sync in v1 (single-machine key only, manual export/import as a later idea).

Full design: [`docs/security/encryption-design.md`](docs/security/encryption-design.md).

### Phase 10 — Companion Architecture Layer ✅ (v1.20, unreleased)

- **Fixed MCP Resources metadata loss**: `handle_list_resources`/`handle_read_resource` previously attached tags/dates/pagination via bare dynamic attributes (`resource.tags = ...`) — not part of the `Resource`/`TextResourceContents` schema, so a spec-compliant client has no obligation to preserve them even though this project's own Pydantic models happened to (`extra = "allow"`). Now attached via the MCP spec's dedicated `_meta` extension field, the correct mechanism for exactly this case. The first resource in a `list_resources` page also carries `pagination` in its `_meta`, fulfilling a contract the docstring already promised but the code never delivered. Tag/date info additionally folds into the human-readable `description` string for clients that only render that.
- **Added `session-handoff` MCP Prompt**: scaffolds the Session Continuity workflow — takes `project` (required) plus optional `status`/`next_steps`/`blockers`, and returns instructions to call `get_or_create_note` + `add_text` with the canonical `Status:`/`Next:`/`Blockers:` format. 3 prompts total now (was 2).
- **Spike: `simplenote://recent`-style auto-context resource — investigated, not building it.** MCP Resources in Claude Desktop are user-attached (picker/attachment UI), not automatically loaded into a conversation at session start — there's no mechanism in the MCP spec or Claude Desktop's client behavior for a server to push a resource into context proactively. A resource the user has to manually attach every session doesn't deliver the "automatic" value the original idea was chasing. The tool-based path (`search_notes`/`get_or_create_note`, now paired with the `session-handoff` prompt) already lets Claude *pull* project-state context autonomously at the start of a conversation, since tools — unlike resources — are always available for the model to call on its own initiative. That's the actual solution to this problem; a curated resource would be redundant with it.

### Phase 11 — Security & Code Quality Audit Remediation ✅ (v1.21, unreleased)

A full repository review (security, runtime correctness, deployment, dependencies, CI, test coverage) surfaced 12 findings, all resolved except the explicitly-deferred one:

- **P0 — Secure HTTP transport**: `MCP_TRANSPORT=http` refuses to start on a non-loopback host without `MCP_HTTP_AUTH_TOKEN` (bearer token, constant-time check); `MCP_HTTP_ALLOWED_HOSTS`/`MCP_HTTP_ALLOWED_ORIGINS` enable DNS-rebinding protection.
- **P0 — Stop logging note plaintext**: tool call arguments (note content, search queries) no longer dumped at INFO; sanitized form only at DEBUG.
- **P1 — Real MCP errors**: tool failures return `CallToolResult(isError=True)` instead of looking like success at the protocol level; failed writes no longer consume the write budget.
- **P1 — Fixed date-filtered search**: both ISO and natural-language (`yesterday`, `3_days_ago`, etc.) date filters now work end-to-end; the natural-language parser itself didn't handle its own advertised underscored format.
- **P1 — Vault key fail-closed**: a corrupted key file/keychain entry is never silently overwritten with a fresh one; `vault_status` reports corruption instead of crashing.
- **P1 — Per-client rate limiting/write budget**: real per-client identity (source IP for HTTP, fixed for stdio) replaces a dead decorator and a global `"default"` bucket.
- **P1 — Repaired Docker/Helm runtime config**: the documented container path now actually serves requests; health/liveness/readiness probes hit real endpoints instead of just checking the package imports — which surfaced and fixed a separate bug where `/health` failed on merely "degraded" status, not just genuine failures.
- **P1 — Restored the excluded test suite**: `simplenote_mcp/tests/` (112 tests) back in CI as an isolated pytest process; fixed the shared-mock bug behind most of its failures.
- **P2 — Supply chain hardening**: all third-party GitHub Actions pinned to commit SHAs; reusable-workflow `secrets: inherit` narrowed to what's actually consumed; production Docker image installs runtime-only dependencies instead of the full dev/test/security toolchain.
- **P2 — Config validation wired up**: `Config.validate()` now runs at startup instead of being dead code.
- **P2 — Packaging metadata consolidated**: `setup.py`'s version/dependency drift fixed and now covered by the consistency checker.
- **P3 — Deferred**: `tool_handlers.py`'s size (3,065 lines) and the 111 broad `except Exception` handlers need focused refactoring behind behavioral tests, not a broad rewrite — tracked as future work, not attempted in this pass.

### Phase 12 — mcp Python SDK v2 Migration ✅ (v1.22, unreleased)

- **Migrated off the deprecated decorator API**: mcp 2.0.0 (2026-07-28) removed the low-level `Server`'s decorator-based handler registration (`@server.list_resources()`, `.read_resource()`, `.list_tools()`, `.call_tool()`, `.list_prompts()`, `.get_prompt()`) in favor of constructor `on_*` callables shaped `(ctx, params) -> Result`. Rather than reshape the existing `handle_*` functions (which every test and internal call site depends on with their pre-2.0 signatures), added a thin adapter layer (`_on_list_resources`, `_on_read_resource`, `_on_list_tools`, `_on_call_tool`, `_on_list_prompts`, `_on_get_prompt` in `server.py`) that bridges the protocol-facing shape to the unchanged `handle_*` functions — zero test call-site churn beyond field-naming fixes below.
- **Replaced `server.request_context`**: the SDK removed this contextvar property in 2.0. `_resolve_client_id()` (per-client rate limiting / write budget identity) now reads a project-owned `_request_ctx_var` contextvar, populated by the `on_call_tool` adapter for the duration of each call.
- **Fixed snake_case field-name breaks**: mcp 2.0's pydantic models expose canonical attributes as snake_case (`is_error`, `input_schema`) — construction kwargs still accept the old camelCase alias (`isError=`, `inputSchema=`), but *attribute reads* do not. Fixed one production read site (`result.isError` → `result.is_error` in `handle_call_tool`'s write-budget check) and the equivalent read sites across the test suite.
- **Bumped `mcp[cli]` to `>=2.0.0,<3.0.0`** in `pyproject.toml` (previously pinned `<2.0.0` as a stopgap — see `requirements-lock.txt`/`requirements-runtime-lock.txt`, regenerated). Both `tests/` (1348 tests) and the legacy `simplenote_mcp/tests/` tree (112 tests) pass with no regressions and no new skips.

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
