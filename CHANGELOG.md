# Changelog

All notable changes to the Simplenote MCP Server project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **`session-handoff` MCP Prompt**: scaffolds the Session Continuity workflow — takes `project`
  (required) plus optional `status`/`next_steps`/`blockers`, and returns instructions to call
  `get_or_create_note` + `add_text` with the canonical `Status:`/`Next:`/`Blockers:` format used
  for cross-session handoff notes. 3 prompts total (was 2).

### Fixed
- **MCP Resources silently dropped tags/dates/pagination metadata**: `handle_list_resources` and
  `handle_read_resource` computed this metadata and attached it via bare dynamic attributes
  (`resource.tags = ...`) that aren't part of the `Resource`/`TextResourceContents` schema — a
  spec-compliant client has no obligation to preserve unrecognized top-level fields. Now attached
  via the MCP spec's dedicated `_meta` extension field, the correct mechanism for this. The first
  resource in a `list_resources` page also now carries `pagination` in its `_meta`, fulfilling a
  contract the docstring already documented but the code never delivered. Tag/date info
  additionally folds into the human-readable `description` string for clients that only render
  that field.
- **Tag-space sanitization inconsistency**: `add_tags` and `remove_tags` called the shared
  `_parse_tags()` sanitizer and discarded its result, then rebuilt the tag list via a separate,
  unsanitized path — `add_tags(tags="my tag")` stored `"my tag"` verbatim while
  `create_note(tags="my tag")` stored `"my-tag"`. A tag added with a space could then never be
  removed via `remove_tags` using the same string, since it no longer matched the hyphenated
  stored form. `update_note` and `rename_tag` had their own separate, also-unsanitized or
  duplicate implementations. All tag-accepting tools — including `search_notes`'s `tags` filter —
  now route through the same `ToolHandlerBase._parse_tags()` sanitizer.
- **`search_notes` returned unbounded results**: the tool schema documents a default `limit` of
  20, but omitting `limit` returned every matching note with no cap. Now enforces the documented
  default (20) and a hard cap of 100, matching `list_notes`'s existing behavior.
- **Notes edited outside Claude were invisible to tag/word search**: notes arriving via
  `BackgroundSync` (e.g. edited in the native Simplenote app) updated the note cache but never
  rebuilt `_tag_index`/`_word_index`/`_title_index` — such notes were retrievable via `get_note`
  but invisible to `list_tags`, tag-filtered `search_notes`, `rename_tag`, and
  `find_untagged_notes`. `_process_sync_notes()` now routes through the same index maintenance
  the create/update tool-handler path uses.
- **Initial cache load skipped title/word indexing**: the non-blocking startup path sets
  `cache._initialized = True` before notes are loaded (by design, to avoid blocking server
  start), which defeats `NoteCache.initialize()`'s own re-entrancy guard — so the
  retry-hardened full initializer (the only code path that built the title/word index) silently
  no-opped, and only the tag index was ever built for notes from the initial background load.
  `_populate_cache_direct()` now builds the full tag/title/word index via the same
  `_build_all_indexes()` used by `initialize()`.

### Changed
- Declared JSON schema for `tags` unified to `array<string>` across all tag-accepting tools
  (`create_note`, `update_note`, `add_tags`, `remove_tags`, `replace_tags`, `search_notes`);
  comma-separated strings are still accepted for backward compatibility.
- `SecurityValidator.validate_arguments()`'s tag count/length/character validation now applies
  to all 8 tag-accepting tools (`create_note`, `update_note`, `add_tags`, `remove_tags`,
  `replace_tags`, `get_or_create_note`, `bulk_tag`), not just 3.

### Docs
- `SECURITY.md` corrected: removed false "encryption at rest" and "memory protection" claims
  (Simplenote itself has no encryption at rest — see the new Data Protection section), refreshed
  the stale version-support table and aspirational quarterly-pentest/annual-audit language to
  reflect this being a solo-maintained open-source project.
- `ROADMAP.md`/`TODO.md` refreshed to the current tool count (27) and version (1.17.1), with the
  next roadmap phases (correctness hardening, opt-in client-side note encryption, companion
  architecture layer) added.
- `ROADMAP.md`/`TODO.md`: documented the outcome of the `simplenote://recent` auto-context
  resource spike — investigated and decided against building it. MCP Resources in Claude Desktop
  are user-attached, not auto-loaded into a conversation at session start, so a curated resource
  wouldn't deliver the "automatic" value the idea was chasing. The existing tool-based path
  (`search_notes`/`get_or_create_note`, now paired with the `session-handoff` prompt) already
  solves proactive context-pulling, since tools — unlike resources — are always available for the
  model to call on its own initiative.

## [1.17.1] - 2026-06-24

### Fixed
- **macOS keychain auth** — `_test_simplenote_connection` now resolves the Simperium token via a
  three-step priority chain: (1) `SIMPLENOTE_TOKEN` env var, (2) the token cached in the macOS
  keychain by the Simplenote desktop app (`security find-generic-password -s chalk-bump-f49`),
  (3) the classic `auth.simperium.com` password endpoint. Steps 1 and 2 completely bypass the
  decommissioned `auth.simperium.com` endpoint that has been returning connection timeouts /
  `token: None` since mid-2025. The Simperium data API (`api.simperium.com`) remains fully
  operational; only the password-auth endpoint is gone.
- Auth failure now surfaces as a clear `AuthenticationError` at startup instead of a cryptic
  `TypeError: expected string or bytes-like object, got 'NoneType'` 75 seconds later deep inside
  urllib's `putheader()`. `_test_simplenote_connection` explicitly calls `authenticate()` and
  raises `AuthenticationError` when the token is `None` or authentication throws.
- `get_note` and `get_note_versions` now return a clean `not_found` error when the Simplenote
  token is `None` (auth failed), instead of leaking the same `TypeError` through the API fallback
  path. Previously both tools crashed when called against an empty cache with bad credentials.
- `get_server_info` debug payload now includes `authenticated` (bool), `cache_healthy` (bool), and
  `last_sync_error` (string or null) so callers can distinguish a healthy empty account from a
  broken-auth state that reports `cache_initialized: true` with `note_count: 0`.
- Log pattern monitor no longer re-processes prior-session log content on startup. The monitor now
  seeks to the current end of each log file when it starts, eliminating a cascade of false-positive
  security alerts (`sql_injection_attempt`, `xss_attempt`, `path_traversal_attempt`,
  `suspicious_user_agent`, `rate_limit_exceeded`) that were triggered every time the server
  restarted because old alert messages matched the very patterns being watched.
- Last authentication error is tracked in module state and cleared on successful auth, so
  `get_server_info` always reflects the current auth state.

## [1.17.0] - 2026-06-22

### Added
- MCP tool annotations (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`) on all
  27 tools so MCP clients can display confirmation UIs for destructive operations
- `SIMPLENOTE_WRITE_MODE` env var (default `false`): write tools are hidden from `list_tools` and
  blocked in `call_tool` unless explicitly enabled, preventing accidental mutations
- Per-session write budget (`SIMPLENOTE_WRITE_BUDGET`, default 20 ops / 60 s rolling window) with a
  human-readable error when exhausted, preventing LLM runaway write loops
- `list_notes` tool: browse recent notes filtered by tag and limit without requiring a search query;
  annotated `readOnlyHint=true`
- Content-shrink guard in `update_note`: refuses to replace a note ≥ 200 chars when new content is
  < 20 % of the original, surfacing `suspicious_shrink` so the LLM can recover gracefully
- No-op detection in `restore_version`: uses cache to detect when the target version matches current
  content and skips the write, returning `no_op=true` without consuming write budget

### Fixed
- Log monitor feedback loop causing up to 2.4 M-line log spam (#585)
- Event loop not closed after use in `log_monitor` background thread
- Makefile `test` and `test-fast` targets pinned to `.venv/bin/pytest`; flaky timing assertion
  loosened to reduce intermittent CI failures

### Dependencies
- mypy upgraded from 1.20.2 to 2.1.0 (major version)
- cryptography upgraded from 48.0.0 to 49.0.0
- mcp (production), starlette, uvicorn, aiohttp, certifi, idna, ruff, pydantic-settings, typer,
  pytest, anyio, and many more updated to latest releases

## [1.16.1] - 2026-05-11

### Fixed
- Three Claude Desktop deployment errors resolved: `psutil.cpu_percent()` called with renamed keyword
  argument (`interval` → positional), security alerter writing to a relative path that fails under
  read-only CWD (`/`), and opaque `TypeError` when Simplenote auth token is `None` (now raises a
  clear `AuthenticationError`)
- Silent note eviction during server start-up: `cache.initialize()` now calls `_evict_if_needed()`
  after loading all notes, preventing data loss when note count exceeds `CACHE_MAX_SIZE`
- `CACHE_MAX_SIZE` default raised from 1 000 to 10 000 to cover most users without extra configuration
- `search_notes` blocking the asyncio event loop: it is now `async` and runs the search engine in a
  thread-pool executor with a 30 s timeout, preventing Boolean AND queries (and other slow searches)
  from permanently hanging the server under Claude Desktop's MCP timeout
- `search_notes` returning far fewer results than expected when using short query terms (e.g. "test"
  missed notes containing "testing"): the word-index pre-filter now uses substring matching, consistent
  with the search engine's `_content_contains()` behaviour

### Tests
- Added real-engine integration tests for `search_notes` (`test_search_integration.py`): six pytest
  tests exercise the full async executor path against an in-memory `NoteCache` fixture (no live
  credentials required), guarding against the production `TypeError: object list can't be used in
  'await' expression` regression, Boolean AND correctness, OR union semantics, substring pre-filter
  inflection matching, 5-second performance bound, and result-set stability
- Fixed `ImportError` in `test_server_capabilities.py` caused by missing public aliases
  (`handle_call_tool`, `handle_list_tools`, `handle_read_resource`) in `test_helpers.py`; aliases
  now forward to the existing `helper_*` functions

## [1.16.0] - 2026-04-28

### Added
- `permanent_delete_note` tool: irreversibly destroy a single note; requires `confirm=true` to execute; returns a dry-run description when `confirm=false` (default) — operation cannot be undone
- `empty_trash` tool: permanently delete all trashed notes in one operation; defaults to `dry_run=true` (lists trashed notes without deleting); requires `dry_run=false` AND `confirm=true` to execute — operation cannot be undone

### Fixed
- `list_tags` returning empty results after startup: `_populate_cache_direct` now calls `_build_tag_index` when loading tagged notes, fixing the issue where `_tag_index` stayed empty because `cache.initialize()` short-circuited on the eagerly-set `_initialized=True` flag (closes #507)
- `log_monitor` background thread exceptions now logged instead of silently swallowed
- Incomplete URL sanitization in `alerting.py` (CodeQL `py/incomplete-url-substring-sanitization`)
- All remaining CodeQL Python findings resolved (`py/empty-except`, `py/import-and-import-from`, wrong-number-of-arguments in integration tests)
- Stale config cache leaking `offline_mode=False` between test runs

### Security
- `cryptography` bumped 46.0.7 → 47.0.0
- Container CVE scan hardened: `ignore-unfixed: true` added to Trivy action; `.trivyignore` added for five CVEs with no available Debian package fix (glibc CVE-2025-4802, linux-pam CVE-2025-6020, perl CVE-2023-31484, sqlite CVE-2025-6965, zlib CVE-2023-45853)
- pip-audit false positive CVE-2026-3219 suppressed (affects CI runner's `pip` tool, not a project dependency)

## [1.15.0] - 2026-04-14

### Added
- `publish_note` tool: publish a note to a public URL by setting the `published` system tag via `update_note`; returns `public_url`; idempotent if already published
- `unpublish_note` tool: remove a note from public access by clearing the `published` system tag; no-op if not published

### Fixed
- Broken `DOCKER_README.md` symlink replaced with real file (symlink target was deleted in doc cleanup, breaking the Docker Hub description CI step)

## [1.14.0] - 2026-04-13

### Added
- `get_server_info` tool: returns server name, version, author, registered tool count, and a debug block (Python version, platform, cache status, sync interval, log level, offline mode)

### Fixed
- `log_monitor._process_log_file`: eliminated unawaited coroutine RuntimeWarning on Python 3.13+ by replacing `run_coroutine_threadsafe` with `loop.run_until_complete()` in background thread context

### Changed
- Python runtime upgraded to 3.13.13 (pyenv); CI `PYTHON_VERSION` updated to match
- Search relevance scoring model documented in `search/engine.py:_calculate_relevance()`

### Removed
- 48 stale historical docs (planning drafts, completed-work summaries, evaluation reports from 2025) superseded by root ROADMAP.md and TODO.md

## [1.13.0] - 2026-04-12

### Added
- `add_text` tool: append a text block to an existing note without fetching the full note first
- `list_tags` tool: list all tags with note counts, sortable by name or count
- `get_note_versions` tool: retrieve version history for a note (up to 10 versions with previews)
- `restore_version` tool: restore a note to a specific historical version
- `rename_tag` tool: rename a tag across all notes atomically, with `dry_run` preview support
- `get_or_create_note` tool: find an existing note by title or create it atomically to avoid duplicates
- `append_to_daily_note` tool: append a timestamped entry to today's daily note, creating it if needed
- `replace_section` tool: replace the content of a named Markdown section without touching other sections
- `find_untagged_notes` tool: list notes with no tags for housekeeping, with configurable limit
- `bulk_tag` tool: add, remove, or set tags on multiple notes in a single operation
- `restore_note` tool: un-trash a deleted note (reverses `delete_note`)
- Tag sanitization: spaces in tags are replaced with hyphens at input time
- `search_notes` supports `pinned`, `created_after`, and `modified_after` filter parameters

### Changed
- Default `SNIPPET_MAX_LENGTH` increased from 100 to 300 characters for richer search result context
- `ResourceNotFoundError` now includes `resource_id` in all tool handlers for better error tracing
- `_parse_tags()` moved to `ToolHandlerBase` so all handlers can use consistent tag parsing
- Tool descriptions updated across all tools with use-vs-alternatives guidance

### Fixed
- `AddTagsHandler`, `RemoveTagsHandler`, `ReplaceTagsHandler` responses now include `tags_added`, `tags_removed`, `tags_now` fields for auditability

## [1.12.1] - 2026-04-08

### Fixed
- Replace deprecated `asyncio.get_event_loop()` with `asyncio.get_running_loop()` across
  `cache.py`, `security.py`, `middleware.py`, `memory_monitor.py`, `log_monitor.py`, and
  `server.py` — eliminates `DeprecationWarning` on Python 3.10+
- Fix memory leak in `SecurityValidator`: `failed_validation_attempts` buckets now capped
  at 500 entries per event type, preventing unbounded growth in long-running servers
- Fix order-dependent test flake in `test_log_monitoring.py` via `reset_log_monitor()`
  singleton reset in `setup_method`
- Fix 4 vacuous `assert True` assertions in `test_phase2_integration.py` with real checks
- Fix isolated test state for all `TestAuthorizationBoundaries` classes — global
  `note_cache` and `simplenote_client` singletons now reset before each test
- Fix `TestConfigSingleton` isolation: add `setup_method` to reset `_config` before tests
- Fix mixed import style in `test_server_advanced.py` (code scanning alert)

### Security
- Memory leak in `SecurityValidator.failed_validation_attempts` patched — unbounded
  accumulation could be exploited to exhaust server memory under sustained load

### Dependencies
- `mcp`: 1.26.0 → 1.27.0
- `aiohttp`: 3.13.4 → 3.13.5
- `requests`: 2.33.0 → 2.33.1
- `uvicorn`: 0.42.0 → 0.43.0
- `pydantic-core`: 2.44.0 → 2.45.0
- `more-itertools`: 10.8.0 → 11.0.1
- `marshmallow`: 4.2.3 → 4.3.0
- `mypy`: 1.19.1 → 1.20.0 (dev)
- `ruff`: 0.15.8 → 0.15.9 (dev)
- `pip-audit`: 2.9.0 → 2.10.0 (dev)
- `click`, `regex`, `charset-normalizer`, `pymdown-extensions`, `pydantic-core` updated

### Internal
- Add `pytest-randomly` to test dependencies; CI uses `--randomly-seed=$GITHUB_RUN_ID`
  for reproducible randomised test ordering
- Harden coverage threshold to 75% hard-fail (was 65% warn-only)
- Add `tests/test_server_handlers.py`: 26 focused tests covering `get_simplenote_client`,
  PID file management, signal handlers, `handle_list_tools` exception fallback,
  `handle_call_tool` unknown-tool and `ServerError` paths, `handle_list_prompts`,
  `handle_get_prompt` (all 3 branches), and `handle_read_resource` invalid-URI /
  cache-miss / not-found paths

## [1.11.0] - 2026-02-25

### 🚀 Minor Release: New Tools, Dependency Refresh, and CI/CD Improvements

This release adds powerful new note management tools, a comprehensive dependency refresh, and resolves CI/CD pipeline failures.

### Added
- **🔍 Fuzzy search** — New `fuzzy_search_notes` tool using thefuzz for approximate string matching
- **📅 Natural language date parsing** — New `search_notes_by_date` tool with human-friendly date expressions (e.g. "last week", "yesterday")
- **📤 Note export** — New `export_notes` tool for bulk export in Markdown, plain text, or JSON formats
- **🔁 Duplicate detection** — New `find_duplicate_notes` tool to identify near-duplicate content across the note collection

### Fixed
- Resolved CI/CD pipeline failures caused by VERSION file corruption
- Added missing `python-dateutil` production dependency to `pyproject.toml`
- Resolved 3 CodeQL code scanning alerts
- Resolved mypy duplicate module detection and untyped import errors
- Addressed additional security review findings

### Dependencies
- 50+ dependency updates via Dependabot including:
  - cryptography: 46.0.3 → 46.0.5 (security fix)
  - nltk: 3.9.1 → 3.9.3 (security fix — GHSA-7p94-766c-hgjp)
  - ruff: 0.14.14 → 0.15.1
  - pydantic-core: 2.33.2 → 2.41.5
  - uvicorn: 0.35.0 → 0.40.0
  - typer: 0.19.1 → 0.23.1
  - setuptools: 80.9.0 → 82.0.0
  - cyclonedx-python-lib: 9.1.0 → 11.6.0
  - psutil: 6.1.1 → 7.2.2
  - pycparser: 2.22 → 3.0
  - coverage: 7.13.1 → 7.13.4
  - pre-commit: 4.2.0 → 4.5.1
  - platformdirs: 4.4.0 → 4.9.1
  - starlette, httpx-sse, packaging, pluggy, pyjwt and many more

### CI/CD
- Removed deprecated `safety` tool from security scanning workflow; fully replaced by `pip-audit`
- Updated pinned ruff version to `0.15.1` in `security.yml` and `auto-fix.yml` workflows, matching `pyproject.toml`
- Performance test threshold adjusted from `0.2s` to `0.5s` for 500-item listings to prevent flaky failures on slower CI runners

### Quality Assurance
- All 975 tests passing with 74% code coverage
- Zero linting errors (Ruff)
- Zero type checking errors (mypy)
- Zero open security alerts (CodeQL, Bandit, pip-audit)
- All CI/CD pipelines passing

## [1.10.1] - 2026-01-26

### 🔧 Patch Release: Security Fixes and Code Quality Improvements

This patch release resolves all CodeQL security alerts and improves code quality through cyclic import fixes.

### Security
- **Resolved all CodeQL code scanning alerts** (0 open alerts)
  - Fixed `py/cyclic-import` issues between error handling modules
  - Fixed `py/repeated-import` patterns across test files
  - Fixed `py/empty-except` patterns with proper documentation
  - Fixed `py/unnecessary-pass` and `py/unused-local-variable` findings
- **Docker image security improvements**
  - Added `apt-get upgrade` to apply security patches in base image
  - Pinned setuptools>=78.1.1 for jaraco.context CVE fix
- **Dismissed infrastructure CVEs** (no upstream fixes available)
  - glibc CVEs in Debian base image (CVE-2026-0861, CVE-2026-0915, CVE-2025-15281)
  - Vendored wheel CVE in setuptools (CVE-2026-24049)

### Fixed
- Resolved cyclic import between `errors.py` and `error_taxonomy.py` by moving `DEFAULT_RESOLUTION_STEPS` to `error_codes.py`
- Fixed CI/CD pipeline failures related to CodeQL and safety package compatibility
- Replaced `safety` with `pip-audit` for dependency vulnerability scanning

### Dependencies
- 47+ dependency updates via Dependabot including:
  - starlette: 0.50.0 → 0.52.1
  - coverage: 7.11.0 → 7.13.1
  - pytest: 8.4.2 → 9.0.2
  - ruff: 0.14.10 → 0.14.14
  - bandit: 1.8.6 → 1.9.3
  - mcp: Updated to latest version
  - cryptography: Updated to 46.0.3

### Quality Assurance
- All 850 tests passing with 73% code coverage
- Zero linting errors (Ruff)
- Zero type checking errors (mypy)
- Zero open security alerts
- All CI/CD pipelines passing

## [1.10.0] - 2026-01-08

### 🔒 Security Release: Critical Vulnerability Fixes and Maintenance Updates

This release addresses a critical security vulnerability in urllib3 and includes comprehensive dependency updates from the past two months.

### Security
- **🔒 Critical**: Fixed CVE-2026-21441 in urllib3 dependency
  - Upgraded urllib3 from 2.6.2 to >=2.6.3
  - Addresses decompression bomb vulnerability in streaming API
  - Prevents excessive resource consumption from malicious servers
  - No known vulnerabilities remaining in dependencies
- Maintained security posture with zero high/critical Bandit findings in production code
- All credentials properly managed via environment variables (no hardcoded secrets)

### Dependencies
- Comprehensive dependency updates via Dependabot (20+ packages)
  - certifi: 2025.11.12 → 2026.1.4
  - filelock: 3.20.1 → 3.20.2
  - sse-starlette: 3.0.4 → 3.1.2
  - coverage: 7.13.0 → 7.13.1
  - psutil: 7.1.3 → 7.2.1
  - pyparsing: 3.2.5 → 3.3.1
  - typer: 0.20.0 → 0.21.0
  - uvicorn: 0.38.0 → 0.40.0
  - python-multipart: 0.0.20 → 0.0.21
  - pre-commit: 4.5.0 → 4.5.1
  - mypy: 1.19.0 → 1.19.1
  - ruff: 0.14.9 → 0.14.10
  - nodeenv: 1.9.1 → 1.10.0
  - mcp[cli]: Updated to latest version

### Fixed
- CI/CD: Restored DOCKER_README.md symlink for Docker Hub description
- CI/CD: Improved handling of disabled auto-merge in Dependabot workflow
- Types: Added missing type hints to http_endpoints.py
- CI/CD: Resolved workflow issues and improved GitHub Actions configuration
- CI/CD: Updated GitHub Actions dependencies (upload-artifact v5→v6, download-artifact v3→v4, cache v4→v5)

### Quality Assurance
- All 831 tests passing with 73% code coverage
- Zero linting errors (Ruff)
- Zero type checking errors (mypy)
- Zero high/critical security issues (Bandit, pip-audit)
- Comprehensive security review completed

## [1.9.0] - 2025-10-28

### 🎉 Major Release: Production-Ready with Critical Performance Fix

This release marks a significant milestone with **98% startup performance improvement** and comprehensive project health enhancements. The server is now **fully production-ready** for Claude Desktop integration.

### Fixed
- **🚀 Critical**: Resolved Claude Desktop timeout by making cache initialization truly async
  - Run blocking Simplenote API calls in thread pool executor to avoid blocking event loop
  - **Reduced server startup time from 55+ seconds to < 1 second** (98% improvement)
  - Fixed `anyio.BrokenResourceError` during shutdown
  - Fixed unawaited coroutine warnings in log monitor
  - Allow graceful operation with empty cache during background loading
  - See `CLAUDE_DESKTOP_TIMEOUT_FIX.md` for detailed technical analysis

### Added
- **📚 Complete documentation suite**
  - Comprehensive CHANGELOG.md with full version history
  - Production validation guide (`TESTING_CLAUDE_DESKTOP.md`)
  - User feedback collection templates
  - GitHub issue templates for bug reports and feature requests
  - Discussion templates for community engagement
  - Detailed project review and health metrics documentation
- **🔧 Code quality improvements**
  - Phase 1 refactoring complete: Reduced high-complexity functions by 21%
  - Cache module complexity reduced from CC 33 to < 10 (100% improvement)
  - Maintainability Index improved from 12.7 to 16.2 (+28%)
  - Extracted 23 helper methods for better code organization
  - See `REFACTORING_PHASE1_COMPLETE.md` for details
- **📊 Enhanced monitoring and metrics**
  - Automated complexity analysis script (`scripts/quality/check_complexity.py`)
  - Performance benchmarking for startup time validation
  - Comprehensive project review documentation

### Changed
- **✨ Project health status**
  - Zero open issues maintained
  - Zero open pull requests maintained
  - Zero diagnostic errors in codebase
  - All 756 tests passing with 69.64% coverage
  - CI/CD pipeline running at 100% success rate
- **📦 Documentation improvements**
  - Updated README with v1.9.0 highlights
  - Enhanced troubleshooting guides
  - Added production deployment best practices
  - Improved contributor guidelines

### Performance
- **Startup time**: 55+ seconds → < 1 second (98% improvement)
- **Test coverage**: Maintained at 69.64% (670 tests)
- **Code complexity**: Functions CC ≥ 15 reduced from 28 to 22 (-21%)
- **Docker image size**: 346MB (optimized multi-stage build)

### Security
- Zero high/critical vulnerabilities
- All security scans passing (Bandit, Safety, CodeQL, Trivy)
- Enhanced input validation and rate limiting
- Regular automated security updates via Dependabot

### Documentation
- Complete version history in CHANGELOG.md
- Production validation guide
- User feedback collection process
- Issue and discussion templates
- Comprehensive project review (Grade A+)

## [1.8.1] - 2025-10-26

### Added
- Comprehensive quality automation and project improvements
- Added comprehensive cache coverage tests (14% → 83% coverage for cache module)
- Test performance script for startup validation
- Enhanced documentation for troubleshooting

### Changed
- Updated TODO.md with 2025-10-20 maintenance actions
- Upgraded actions/setup-node from v5 to v6 in CI/CD workflows

### Fixed
- Corrected Python 3.14 site-packages path in Docker builds

### Dependencies
- Upgraded MCP library from 1.14.0 to 1.18.0
- Upgraded Ruff from 0.14.0 to 0.14.1
- Upgraded pytest from 8.4.1 to 8.4.2
- Upgraded pytest-asyncio from 1.1.0 to 1.2.0
- Upgraded pytest-cov from 6.2.1 to 7.0.0
- Upgraded mypy from 1.18.1 to 1.18.2
- Upgraded coverage from 7.8.2 to 7.11.0
- Multiple dependency updates via Dependabot (pydantic, uvicorn, idna, etc.)

## [1.8.0] - 2025-10-19

### Changed
- Major dependency refresh to latest stable versions
- Improved metrics collection and monitoring

### Dependencies
- Updated multiple production and development dependencies to latest versions

## [1.7.0] - 2025-10-14

### Added
- CodeQL security analysis integration
- Enhanced CI/CD pipeline with security scanning
- Improved Docker multi-stage builds

### Fixed
- Resolved CodeQL and Trivy scanner failures in CI
- Fixed integration test failures in CI offline mode
- Updated workflow badge references in README
- Installed build package for CI and local testing

### Changed
- Upgraded Docker base image to Python 3.14-slim
- Upgraded GitHub Actions dependencies

## [1.6.0] - 2025-09

### Added
- MCP evaluations framework integration
- Comprehensive test suite with 700+ tests
- Performance monitoring and metrics collection
- Security hardening with multiple scanning tools
- HTTP endpoints for health and metrics
- Advanced search with boolean operators
- Tag filtering and pagination support

### Changed
- Improved cache performance with background synchronization
- Enhanced error handling and taxonomy
- Better logging and diagnostics

### Security
- Added Bandit security scanning
- Added pip-audit vulnerability scanning
- Added Trivy container scanning
- Implemented rate limiting and DoS protection
- Enhanced input validation and sanitization

## [1.5.0] - 2025-08

### Added
- Docker and Kubernetes deployment support
- Helm charts for production deployments
- Background cache synchronization
- Rate limiting middleware
- Security monitoring and alerting

### Changed
- Refactored server architecture for better modularity
- Improved error handling with custom error taxonomy
- Enhanced documentation with deployment guides

## [1.4.0] - 2025-07

### Added
- MCP protocol 2024-11-05 support
- Prompts capability for note templates
- Resources capability for note listing
- Tools capability for note management
- Basic caching implementation

### Changed
- Migrated to MCP Python SDK 1.0+
- Updated authentication to use environment variables
- Improved note search functionality

## [1.3.0] - 2025-06

### Added
- Tag management support
- Note filtering by tags
- Pagination for note lists

### Changed
- Improved note content parsing
- Better error messages

## [1.2.0] - 2025-05

### Added
- Note update functionality
- Note deletion (trash) functionality
- Search query support

### Changed
- Enhanced note listing with sorting
- Improved connection handling

## [1.1.0] - 2025-04

### Added
- Note creation capability
- Basic note listing
- Initial MCP integration

### Changed
- Refactored to use Simplenote Python library
- Improved logging

## [1.0.0] - 2025-03

### Added
- Initial release
- Basic Simplenote authentication
- Read-only note access
- Simple MCP server implementation

---

## Version History Summary

- **1.11.0** (Current) - 🚀 New tools (fuzzy search, date search, export, duplicates), dependency refresh, CI/CD fixes
- **1.10.1** - 🔒 Security fixes, CodeQL alerts resolved, dependency updates
- **1.10.0** - 🔒 Critical urllib3 CVE fix, comprehensive dependency updates
- **1.9.0** - 🎉 Production-ready release with 98% startup performance improvement
- **1.8.1** - Quality improvements, dependency updates, Claude Desktop fix preparation
- **1.8.0** - Major dependency refresh
- **1.7.0** - Security enhancements, CI/CD improvements
- **1.6.0** - Comprehensive testing, monitoring, advanced features
- **1.5.0** - Docker/Kubernetes support, production features
- **1.4.0** - Full MCP protocol implementation
- **1.3.0** - Tag management
- **1.2.0** - Note editing capabilities
- **1.1.0** - Note creation
- **1.0.0** - Initial release

[1.15.0]: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.14.0...v1.15.0
[1.14.0]: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.13.0...v1.14.0
[1.13.0]: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.12.1...v1.13.0
[1.12.1]: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.12.0...v1.12.1
[1.12.0]: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.11.0...v1.12.0
[1.11.0]: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.10.1...v1.11.0
[1.10.1]: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.10.0...v1.10.1
[1.10.0]: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.9.0...v1.10.0
[1.9.0]: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.8.1...v1.9.0
[1.12.1]: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.12.0...v1.12.1
[1.12.0]: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.10.1...v1.12.0
[1.10.1]: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.10.0...v1.10.1
[1.10.0]: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.9.0...v1.10.0
[1.9.0]: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.8.1...v1.9.0
[Unreleased]: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.17.0...HEAD
[1.17.0]: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.16.1...v1.17.0
[1.16.1]: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.16.0...v1.16.1
[1.16.0]: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.15.0...v1.16.0
[1.8.1]: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.8.0...v1.8.1
[1.8.0]: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.7.0...v1.8.0
[1.7.0]: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.6.0...v1.7.0
[1.6.0]: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.5.0...v1.6.0
[1.5.0]: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.4.0...v1.5.0
[1.4.0]: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/docdyhr/simplenote-mcp-server/releases/tag/v1.0.0
