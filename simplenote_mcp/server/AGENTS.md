# simplenote_mcp/server/

## Purpose

Core MCP server package: protocol handlers, tool registry, note cache, credential resolution, security/rate-limit middleware, and opt-in vault encryption. Flat file layout — no further nesting except `search/` and `monitoring/` (own child docs) and `compat/`/`utils/` (small, covered here).

## Ownership

- `server.py` — MCP protocol handlers (`handle_list_tools`, `handle_call_tool`, etc.), Simplenote client singleton, `WRITE_TOOLS` gate, write-budget tracking, background cache init.
- `tool_handlers.py` — one `ToolHandlerBase` subclass per tool, registered in `ToolHandlerRegistry`.
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

- **Tool-handler pattern**: adding a tool touches three places — the `XHandler(ToolHandlerBase)` class in `tool_handlers.py`, one line in `ToolHandlerRegistry._handlers`, and a `types.Tool(...)` schema entry in `server.py::handle_list_tools()`. Any handler that mutates Simplenote data must also be added to the `WRITE_TOOLS` frozenset in `server.py`, or it bypasses both the `SIMPLENOTE_WRITE_MODE` gate and the per-client write-budget check (`_check_write_budget`/`_record_write`).
- **Credential resolution** (`keychain.py::get_simperium_token`): local file cache at `~/.config/simplenote-mcp/<email>.token` (mode `0600`, `os.open(..., mode=0o600)` for atomic restrictive creation — never write-then-chmod) → macOS Keychain entry used by Simplenote Desktop (`chalk-bump-f49`) → password fallback in `server.py::_test_simplenote_connection()`. No note-content encryption exists outside the opt-in Vault feature; Simplenote itself has no encryption at rest.
- **`cache_utils.py::CacheManager.get_or_create_note` is dead code**: it calls the synchronous `sn.get_note()` directly inside an `async def` with no executor/timeout wrapping, which would block the event loop if ever wired up. The live `get_or_create_note` tool is `tool_handlers.py::GetOrCreateNoteHandler`, which correctly wraps its blocking Simplenote API call in `loop.run_in_executor(...)` with `asyncio.wait_for(..., timeout=30.0)`. Do not route through `CacheManager.get_or_create_note` without adding the same guard.
- **Offline mode** (`SIMPLENOTE_OFFLINE_MODE=true`): the mock client in `server.py::get_simplenote_client()` stubs `add_note`/`get_note`/`update_note` to return `({}, 0)` — an empty dict with no `'key'` field. Tests asserting on `note['key']` will fail against this mock.
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

- `search/AGENTS.md` — query parser and boolean/fuzzy/date search engine
- `monitoring/AGENTS.md` — metrics collection and alerting thresholds
