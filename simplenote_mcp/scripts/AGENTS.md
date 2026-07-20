# simplenote_mcp/scripts/

## Purpose

Runtime diagnostics and dev-workflow scripts shipped alongside the package (distinct from top-level `scripts/`, which is CI/quality tooling only). See `README.md` in this folder for per-script usage.

## Ownership

- Server management: `restart_claude.sh`, `cleanup_servers.sh`, `check_server_pid.sh`, `watch_logs.sh` — operate on the locally running Claude Desktop / MCP server process.
- Diagnostics: `diagnose_api.py` (Simplenote API connectivity), `analyze_logs.py`, `log_format_test.py`, `logging_examples.py`, `error_examples.py`, `monitoring_dashboard.py` (terminal UI for `server/monitoring/metrics.py`).
- Test/coverage helpers: `generate_test_coverage.py`, `live_test_redesign.py`.
- Verification: `verify_tools.sh`, `test_tool_visibility.sh` — confirm tools are registered and visible to Claude.
- `release.sh` — bumps version and tags a release; refuses to run with a dirty working tree.
- `config.sh` — shared shell config sourced by the `.sh` scripts here.

## Local Contracts

- `restart_claude.sh` and `cleanup_servers.sh` kill running processes (Claude Desktop / MCP server) — confirm with the user before running against a session with unsaved state elsewhere.
- `release.sh` tags and can push a release; it is a manual, deliberate action, not something to run as a side effect of an unrelated task.
- These scripts assume a local macOS Claude Desktop installation (paths, `restart_claude.sh` process names) — not portable CI tooling.

## Verification

None — these are interactive/manual diagnostic tools, not part of the automated test suite.

## Child DOX Index

None.
