# tests/

## Purpose

Primary, CI-wired pytest tree (`testpaths = ["tests"]` in `pyproject.toml`) — 60 test files. All new tests go here, not in the legacy `simplenote_mcp/tests/` tree (see that folder's `AGENTS.md`).

## Ownership

- One `test_*.py` per source module/feature area (e.g. `test_cache.py`, `test_advanced_search.py`, `test_tool_handlers*.py`, `test_auth*.py`, `test_config.py`).
- `conftest.py` — shared fixtures, all autouse unless noted: `isolate_token_file_cache` (redirects the keychain token-cache path to `tmp_path`), `reset_write_budget`, `reset_config_cache`, plus non-autouse `mock_simplenote_client`, `simplenote_env_vars`, `server_context`, `authenticated_context`.
- `fixtures_rate_limit.py`, `fixtures_retry.py` — shared fixture modules for rate-limit/retry test scenarios.
- `unit/` — currently empty; `test_server_comprehensive.py.disabled` / `test_server_integration.py.disabled` at this level are intentionally disabled, not stale cruft to delete without checking why first.

## Local Contracts

- Run with `SIMPLENOTE_OFFLINE_MODE=true` — real Simplenote credentials must never be required to run this suite.
- Coverage gate: `--cov-fail-under=75` (`pyproject.toml` `addopts`).
- Markers available: `unit`, `integration`, `perf`, `security`, `slow`, `network`, `auth`, `offline` (`--strict-markers` enforced — unregistered markers fail collection).
- Do not merge this tree's pytest invocation with `simplenote_mcp/tests/` — both mutate process-global singletons (see `simplenote_mcp/server/monitoring/AGENTS.md`) and only reset state for their own tests.
- Offline-mode mock client (`server.py::get_simplenote_client()`) returns `({}, 0)` from `add_note`/`get_note`/`update_note` — don't write assertions expecting a populated `note['key']` against the raw mock.

## Work Guidance

- New tool handler → add tests here, not in `simplenote_mcp/tests/`, per `simplenote_mcp/server/AGENTS.md`'s tool-handler pattern.
- Prefer existing fixtures (`mock_simplenote_client`, `authenticated_context`) over hand-rolled mocks; grep for the symbol's real import path before mocking — mock where it's *used*, not where it's defined.

## Verification

- `make test-fast` — `SIMPLENOTE_OFFLINE_MODE=true .venv/bin/pytest tests/ -x -q --timeout=30`

## Child DOX Index

None.
