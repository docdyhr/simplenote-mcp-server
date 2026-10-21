# simplenote_mcp/server/

## Purpose

Core MCP server package: protocol handlers, tool registry, note cache, credential resolution, security/rate-limit middleware, and opt-in vault encryption. Flat file layout — no further nesting except `tool_handlers/`, `search/` and `monitoring/` (own child docs) and `compat/`/`utils/` (small, covered here).

## Ownership

- `server.py` — MCP protocol handlers (`handle_list_tools`, `handle_call_tool`, resources, the mcp 2.0 `on_*` adapters), Simplenote client singleton, `WRITE_TOOLS` gate, write-budget tracking, background cache init, stdio/HTTP transports.
- `tool_schemas.py` — every tool's `types.Tool` schema: `build_read_tools()` (always advertised), `build_write_tools()` (write mode only), `build_fallback_tools()`. `server.py::handle_list_tools` chooses which lists to return.
- `prompts.py` — `handle_list_prompts`/`handle_get_prompt` prompt templates; re-exported from `server.py`, which registers them.
- `tool_handlers/` — one `ToolHandlerBase` subclass per tool, grouped by domain, registered in `ToolHandlerRegistry` (`tool_handlers/registry.py`); see `tool_handlers/AGENTS.md`.
- `cache.py` — `NoteCache`: in-memory cache, background sync, search indexing. `cache_utils.py` — cache helper functions; note its `CacheManager.get_or_create_note` method (see Local Contracts) is dead code, not the live tool path.
- `config.py` — environment-based `Config` singleton (`SIMPLENOTE_EMAIL`/`SIMPLENOTE_PASSWORD`, `SIMPLENOTE_OFFLINE_MODE`, `SYNC_INTERVAL_SECONDS`, `LOG_LEVEL`, write-budget settings, HTTP transport settings).
- `security.py` — `validate_tool_security` decorator and input validators. `middleware.py` — `RateLimiter`, `RequestValidator`, `AuthenticationMiddleware`. `decorators.py` — composes these onto handlers.
- `errors.py` / `error_codes.py` / `error_helpers.py` / `error_taxonomy.py` — exception hierarchy and MCP-facing error formatting.
- `auth.py` / `keychain.py` — Simperium token resolution (see Local Contracts).
- `vault.py` — opt-in client-side AES-256-GCM note encryption (`encrypt_note`/`decrypt_note`/`vault_status` tools).
- `logging.py` / `logger_factory.py` / `log_monitor.py` / `alerting.py` — structured logging, log tailing, threshold alerting.
- `duplicates.py`, `export.py`, `http_endpoints.py`, `context.py`, `mcp_types_compat.py` — single-purpose support modules.
- `compat/`, `utils/` — small compatibility shims and shared helpers (content-type detection, common utilities); no independent rules beyond this doc.

## Local Contracts

- **Tool-handler pattern**: adding a tool touches three places — the `XHandler(ToolHandlerBase)` class in its domain module under `tool_handlers/` (exported from `tool_handlers/__init__.py`), one line in `ToolHandlerRegistry._handlers` (`tool_handlers/registry.py`), and a `types.Tool(...)` schema entry in `tool_schemas.py` (`build_read_tools()`, or `build_write_tools()` for a mutating tool). Any handler that mutates Simplenote data must also be added to the `WRITE_TOOLS` frozenset in `server.py`, or it bypasses both the `SIMPLENOTE_WRITE_MODE` gate and the per-client write-budget check (`_check_write_budget`/`_record_write`).
- **Credential resolution** (`keychain.py::get_simperium_token`): local file cache at `~/.config/simplenote-mcp/<email>.token` (mode `0600`, `os.open(..., mode=0o600)` for atomic restrictive creation — never write-then-chmod) → macOS Keychain entry used by Simplenote Desktop (`chalk-bump-f49`) → password fallback in `server.py::_test_simplenote_connection()`. No note-content encryption exists outside the opt-in Vault feature; Simplenote itself has no encryption at rest.
- **`cache_utils.py::CacheManager.get_or_create_note` is dead code**: it calls the synchronous `sn.get_note()` directly inside an `async def` with no executor/timeout wrapping, which would block the event loop if ever wired up. The live `get_or_create_note` tool is `tool_handlers/notes.py::GetOrCreateNoteHandler`, which correctly wraps its blocking Simplenote API call in `loop.run_in_executor(...)` with `asyncio.wait_for(..., timeout=30.0)`. Do not route through `CacheManager.get_or_create_note` without adding the same guard.
- **Offline mode** (`SIMPLENOTE_OFFLINE_MODE=true`): `server.py::_build_offline_mock_client()` returns a `MagicMock` whose `add_note`/`get_note`/`update_note`/`trash_note` share an in-memory store (notes get `mock-note-N` keys; unknown keys return `(None, -1)`), and `get_note_list` returns `([], 0)`. Only this client has `OFFLINE_CLIENT_MARKER` set to `True` (compare with `is True`: any other MagicMock answers with a truthy mock). `_test_simplenote_connection` then skips token acquisition, so mock usernames and tokens never reach `keychain.py`'s file cache. Before 2026-10-21 they did, leaving zero-byte `<MagicMock …>.token` files.
- **Health/metrics endpoint auth** (`http_endpoints.py::HTTPEndpointsServer.start()` / `HTTPEndpointsHandler._is_authorized`): `ENABLE_HTTP_ENDPOINT`'s `/health`, `/ready`, `/metrics`, `/thresholds` server refuses to start on a non-loopback `HTTP_HOST` unless `HTTP_ENDPOINT_AUTH_TOKEN` is set — mirrors the MCP HTTP transport's own `MCP_HTTP_AUTH_TOKEN` guard in `server.py::run_http()`. Loopback callers are always trusted regardless of whether a token is configured (checked via `self.client_address`, not the bind address), so the container's own `exec`-based liveness/readiness probe never needs the secret on its command line. Any new listening socket added to this package should get the same non-loopback-requires-auth treatment.
- **No hardcoded credentials** — environment variables and the keychain chain only.

## Work Guidance

- Follow existing error-hierarchy conventions (`errors.py`/`error_taxonomy.py`) for new failure modes rather than raising bare exceptions.
- Google-style docstrings, full type hints, Ruff-formatted (88 char line length).

## Verification

- `make test-fast` (primary tree, exercises most of this package)
- `mypy simplenote_mcp`
- `bandit -c pyproject.toml -r simplenote_mcp`

## Child DOX Index

- `tool_handlers/AGENTS.md` — per-tool handler classes, grouped by domain, and the dispatch registry
- `search/AGENTS.md` — query parser and boolean/fuzzy/date search engine
- `monitoring/AGENTS.md` — metrics collection and alerting thresholds
