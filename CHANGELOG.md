# Changelog

All notable changes to the Simplenote MCP Server project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `get_server_info` tool: returns server name, version, author, registered tool count, and a debug block (Python version, platform, cache status, sync interval, log level, offline mode)

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

[Unreleased]: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.13.0...HEAD
[1.13.0]: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.12.1...v1.13.0
[1.12.1]: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.12.0...v1.12.1
[1.12.0]: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.11.0...v1.12.0
[1.11.0]: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.10.1...v1.11.0
[1.10.1]: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.10.0...v1.10.1
[1.10.0]: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.9.0...v1.10.0
[1.9.0]: https://github.com/docdyhr/simplenote-mcp-server/compare/v1.8.1...v1.9.0
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
